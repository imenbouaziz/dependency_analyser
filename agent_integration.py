"""
agent_integration.py
Example integration of the Ollama agent with MCP server tools.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import DependencyAgent, create_ollama_client
from mcp_server.server import STATE
from mcp_server.graph.impact_analysis import impact_summary
from mcp_server.graph.recommendations import recommend_upgrade
from mcp_server.graph.sbom_generator import generate_minimal_sbom


def run_agent_query(query: str, verbose: bool = True):
    """
    Run an agent query using the loaded dependency graph.
    
    Args:
        query: Natural language query about dependencies
        verbose: Whether to show intermediate steps
    
    Returns:
        Agent's response
    """
    # Check if graph is loaded
    if not STATE.get("graph"):
        return "Error: No dependency graph loaded. Please run the server with --repo first."
    
    # Create agent
    llm = create_ollama_client()
    agent = DependencyAgent(llm=llm, verbose=verbose)
    
    # Register MCP tools as agent tools
    agent.register_tool(
        "artifact_impact",
        lambda artifact_coord: impact_summary(STATE["graph"], artifact_coord),
        "Analyze which modules depend on a specific artifact (format: group:artifact:version)"
    )
    
    agent.register_tool(
        "artifact_recommendation",
        lambda artifact_coord, policy="latest_patch": recommend_upgrade(artifact_coord, policy),
        "Get version upgrade recommendations for an artifact"
    )
    
    agent.register_tool(
        "export_sbom",
        lambda project_name=None: generate_minimal_sbom(
            STATE["graph"],
            project_name or STATE.get("project_name", "project")
        ),
        "Generate a CycloneDX SBOM for the project"
    )
    
    # Build context
    context = {
        "project_name": STATE.get("project_name", "unknown"),
        "repo_path": STATE.get("repo_path", "unknown"),
        "graph_stats": {
            "nodes": len(STATE["graph"].get("nodes", [])),
            "edges": len(STATE["graph"].get("edges", []))
        }
    }
    
    # Run agent
    response = agent.run(query, context=context)
    
    return response


def interactive_mode():
    """
    Start an interactive chat session with the agent.
    """
    print("\n" + "="*70)
    print(" Dependency Analyzer Agent - Interactive Mode")
    print("="*70)
    print("\nAsk questions about your dependencies!")
    print("Commands: 'quit' or 'exit' to stop, 'reset' to clear history\n")
    
    if not STATE.get("graph"):
        print("⚠️  Warning: No dependency graph loaded.")
        print("   Run the server with --repo first to load a project.\n")
        return
    
    # Show project info
    print(f"📦 Project: {STATE.get('project_name', 'unknown')}")
    print(f"📊 Graph: {len(STATE['graph'].get('nodes', []))} nodes, "
          f"{len(STATE['graph'].get('edges', []))} edges\n")
    
    # Create agent
    llm = create_ollama_client()
    agent = DependencyAgent(llm=llm, verbose=False)
    
    # Register tools
    agent.register_tool(
        "artifact_impact",
        lambda artifact_coord: impact_summary(STATE["graph"], artifact_coord)
    )
    agent.register_tool(
        "artifact_recommendation",
        lambda artifact_coord, policy="latest_patch": recommend_upgrade(artifact_coord, policy)
    )
    agent.register_tool(
        "export_sbom",
        lambda project_name=None: generate_minimal_sbom(
            STATE["graph"],
            project_name or STATE.get("project_name", "project")
        )
    )
    
    # Chat loop
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n👋 Goodbye!\n")
                break
            
            if user_input.lower() == 'reset':
                agent.conversation_history = []
                print("\n✅ Conversation history reset.\n")
                continue
            
            print("\n🤖 Agent: ", end="", flush=True)
            
            # Get response
            response = agent.chat(user_input)
            print(response)
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dependency Analyzer Agent CLI")
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to run (non-interactive)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start interactive chat mode"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show agent's thinking process"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.query:
        result = run_agent_query(args.query, verbose=args.verbose)
        print("\n" + "="*70)
        print("Agent Response:")
        print("="*70)
        print(result)
    else:
        parser.print_help()
