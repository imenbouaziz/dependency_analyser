"""
app.py
Streamlit UI for Dependency Analyzer Tool
"""

import streamlit as st
import sys
import os
from typing import Dict, Optional
from streamlit_agraph import agraph, Node, Edge, Config

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.utils.filesystem import clone_or_use_local, detect_ecosystem, get_project_name
from mcp_server.scanners.maven_scanner import scan_maven_repo, scan_maven_repo_with_code_analysis
from mcp_server.parsers.maven_parser import parse_maven_module
from mcp_server.graph.graph_builder import build_graph
from mcp_server.graph.impact_analysis import impact_summary
from mcp_server.graph.recommendations import recommend_upgrade
from mcp_server.graph.sbom_generator import generate_minimal_sbom
from mcp_server.client import SimpleMCPClient

# Try to import agent (optional - works without Ollama)
try:
    from agent import DependencyAgent, create_ollama_client
    AGENT_AVAILABLE = True
except Exception as e:
    AGENT_AVAILABLE = False
    print(f"Agent import failed: {e}")

# Page configuration
st.set_page_config(
    page_title="Dependency Analyzer",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if "graph" not in st.session_state:
    st.session_state.graph = None
if "project_name" not in st.session_state:
    st.session_state.project_name = None
if "repo_path" not in st.session_state:
    st.session_state.repo_path = None
if "ecosystem" not in st.session_state:
    st.session_state.ecosystem = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent" not in st.session_state and AGENT_AVAILABLE:
    st.session_state.agent = None
if "code_analysis" not in st.session_state:
    st.session_state.code_analysis = None
if "class_dependencies" not in st.session_state:
    st.session_state.class_dependencies = None
if "mcp_client" not in st.session_state:
    st.session_state.mcp_client = None

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #555;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def scan_repository(repo_path_or_url: str) -> Dict:
    """Scan and analyze a repository."""
    with st.spinner("🔍 Processing repository..."):
        # Step 1: Clone or use local
        repo_result = clone_or_use_local(repo_path_or_url)
        if not repo_result["success"]:
            return {"error": repo_result.get("error", "Failed to access repository")}
        
        repo_path = repo_result["path"]
        
        # Step 2: Detect ecosystem
        ecosystem = detect_ecosystem(repo_path)
        if not ecosystem:
            return {"error": f"Could not detect build system in {repo_path}"}
        
        st.session_state.ecosystem = ecosystem
        
        # Step 3: Scan based on ecosystem (WITH code analysis)
        if ecosystem == "maven":
            st.info("🔍 Performing enhanced scan with static code analysis...")
            scan_result = scan_maven_repo_with_code_analysis(repo_path, analyze_code=True)
            
            # Store code analysis separately
            if "code_analysis" in scan_result:
                st.session_state.code_analysis = scan_result["code_analysis"]
            
            # Store class dependencies separately
            if "class_dependencies" in scan_result:
                st.session_state.class_dependencies = scan_result["class_dependencies"]
        else:
            return {"error": f"{ecosystem.capitalize()} support coming soon!"}
        
        if "error" in scan_result:
            return scan_result
        
        # Step 4: Parse modules
        parsed_modules = []
        modules = scan_result.get("modules", [])
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, module in enumerate(modules):
            module_path = module.get("path")
            module_name = module.get("name", "unknown")
            
            status_text.text(f"Parsing module {i+1}/{len(modules)}: {module_name}")
            
            if module_path and ecosystem == "maven":
                parse_result = parse_maven_module(module_path)
                if "error" not in parse_result:
                    parsed_modules.append(parse_result)
                    st.write(f"✅ Parsed {module_name}: {len(parse_result.get('dependencies', []))} dependencies found")
                else:
                    st.warning(f"⚠️ Could not parse {module_name}: {parse_result.get('error', 'Unknown error')}")
            progress_bar.progress((i + 1) / len(modules))
        
        status_text.empty()
        
        if not parsed_modules:
            return {"error": "No modules could be parsed"}
        
        # Step 5: Build graph
        graph = build_graph(parsed_modules)
        
        # Update session state
        st.session_state.graph = graph
        st.session_state.project_name = get_project_name(repo_path)
        st.session_state.repo_path = repo_path
        
        # Update MCP client with new graph
        if st.session_state.mcp_client is None:
            st.session_state.mcp_client = SimpleMCPClient(
                graph=graph,
                project_name=st.session_state.project_name
            )
        else:
            st.session_state.mcp_client.update_graph(graph)
            st.session_state.mcp_client.update_project_name(st.session_state.project_name)
        
        return {
            "success": True,
            "ecosystem": ecosystem,
            "project_name": st.session_state.project_name,
            "modules": len(parsed_modules),
            "nodes": len(graph.get("nodes", [])),
            "edges": len(graph.get("edges", []))
        }

def generate_neo4j_cypher(graph: Dict, project_name: str) -> str:
    """Generate Neo4j Cypher queries to import the dependency graph."""
    cypher_lines = [
        "// Neo4j Cypher Import Script",
        f"// Project: {project_name}",
        "// Generated by Dependency Analyzer",
        "",
        "// Clear existing data (optional - comment out if you want to merge)",
        "// MATCH (n) DETACH DELETE n;",
        "",
        "// Create Module Nodes",
    ]
    
    # Create nodes
    for node in graph.get("nodes", []):
        node_id = node.get("id", "").replace("'", "\\'")
        node_type = node.get("type", "")
        
        if node_type == "module":
            module_name = node_id.replace("module:", "")
            ecosystem = node.get("meta", {}).get("ecosystem", "unknown")
            source = node.get("meta", {}).get("source", "").replace("\\", "\\\\").replace("'", "\\'")
            
            cypher_lines.append(
                f"CREATE (:{node_type} {{id: '{node_id}', name: '{module_name}', ecosystem: '{ecosystem}', source: '{source}'}});"
            )
        elif node_type == "artifact":
            artifact_coord = node_id.replace("artifact:", "")
            parts = artifact_coord.split(":")
            group = parts[0] if len(parts) > 0 else ""
            artifact = parts[1] if len(parts) > 1 else ""
            version = parts[2] if len(parts) > 2 else ""
            scope = node.get("meta", {}).get("scope", "")
            
            cypher_lines.append(
                f"CREATE (:{node_type} {{id: '{node_id}', coordinate: '{artifact_coord}', group: '{group}', artifact: '{artifact}', version: '{version}', scope: '{scope}'}});"
            )
    
    cypher_lines.append("")
    cypher_lines.append("// Create Relationships")
    
    # Create relationships
    for edge in graph.get("edges", []):
        from_id = edge.get("from", "").replace("'", "\\'")
        to_id = edge.get("to", "").replace("'", "\\'")
        relation = edge.get("meta", {}).get("relation", "DEPENDS_ON").upper()
        
        cypher_lines.append(
            f"MATCH (a {{id: '{from_id}'}}), (b {{id: '{to_id}'}}) CREATE (a)-[:{relation}]->(b);"
        )
    
    cypher_lines.append("")
    cypher_lines.append("// Create indexes for better performance")
    cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (n:module) ON (n.id);")
    cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (n:artifact) ON (n.id);")
    cypher_lines.append("CREATE INDEX IF NOT EXISTS FOR (n:artifact) ON (n.coordinate);")
    
    return "\n".join(cypher_lines)

def init_agent():
    """Initialize the AI agent with MCP client."""
    if AGENT_AVAILABLE and st.session_state.agent is None:
        try:
            # Initialize MCP client if not already done
            if st.session_state.mcp_client is None:
                st.session_state.mcp_client = SimpleMCPClient(
                    graph=st.session_state.graph,
                    project_name=st.session_state.project_name,
                    session_state=st.session_state
                )
            
            llm = create_ollama_client()
            agent = DependencyAgent(llm=llm, verbose=False)
            
            # Register MCP tools with the agent
            mcp = st.session_state.mcp_client
            
            agent.register_tool(
                "scan_repository",
                lambda repo_path_or_url: mcp.scan_repository(repo_path_or_url),
                "Scan and analyze a repository (local path or Git URL)"
            )
            agent.register_tool(
                "artifact_impact",
                lambda artifact_coord: mcp.artifact_impact(artifact_coord),
                "Analyze which modules depend on a specific artifact (format: group:artifact:version)"
            )
            agent.register_tool(
                "artifact_recommendation",
                lambda artifact_coord, policy="latest_patch": mcp.artifact_recommendation(artifact_coord, policy),
                "Get version upgrade recommendations for an artifact"
            )
            agent.register_tool(
                "export_sbom",
                lambda project_name=None: mcp.export_sbom(project_name),
                "Generate a CycloneDX SBOM for the project"
            )
            
            st.session_state.agent = agent
            return True
        except Exception as e:
            st.error(f"Failed to initialize agent: {str(e)}")
            return False
    return st.session_state.agent is not None

# Header
st.markdown('<div class="main-header">📦 Dependency Analyzer</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Repository input
    repo_input = st.text_input(
        "Repository Path or URL",
        placeholder="C:\\path\\to\\project or https://github.com/user/repo",
        help="Enter a local filesystem path or a GitHub repository URL"
    )
    
    analyze_button = st.button("🔍 Analyze Repository", type="primary", use_container_width=True)
    
    if analyze_button and repo_input:
        if not AGENT_AVAILABLE:
            st.error("❌ AI Agent not available. Cannot perform analysis.")
        else:
            # Initialize agent first
            if init_agent():
                with st.spinner("🤖 Agent is analyzing repository..."):
                    # Ask agent to scan repository
                    response = st.session_state.agent.run(
                        f"Scan and analyze this repository: {repo_input}",
                        context={"action": "scan_repository", "repo_path": repo_input}
                    )
                    
                    # Check if successful
                    if st.session_state.graph:
                        st.success(f"✅ Successfully analyzed {st.session_state.project_name}!")
                        st.rerun()
                    else:
                        st.error(f"❌ Analysis failed. Agent response: {response}")
            else:
                st.error("❌ Failed to initialize agent")
    
    st.divider()
    
    # Project info
    if st.session_state.graph:
        st.subheader("📊 Project Info")
        st.write(f"**Name:** {st.session_state.project_name}")
        st.write(f"**Ecosystem:** {st.session_state.ecosystem or 'Unknown'}")
        st.write(f"**Nodes:** {len(st.session_state.graph.get('nodes', []))}")
        st.write(f"**Edges:** {len(st.session_state.graph.get('edges', []))}")
        
        # MCP connection status
        if st.session_state.mcp_client:
            st.success("🔌 MCP Client: Connected")
        else:
            st.warning("🔌 MCP Client: Not initialized")
        st.write(f"**Nodes:** {len(st.session_state.graph.get('nodes', []))}")
        st.write(f"**Edges:** {len(st.session_state.graph.get('edges', []))}")
        
        if st.button("🗑️ Clear Project", use_container_width=True):
            st.session_state.graph = None
            st.session_state.project_name = None
            st.session_state.repo_path = None
            st.session_state.ecosystem = None
            st.session_state.chat_history = []
            st.rerun()
    
    st.divider()
    
    # AI Agent status
    st.subheader("🤖 AI Agent")
    if AGENT_AVAILABLE:
        st.success("✅ Ollama available")
    else:
        st.info("ℹ️ AI features disabled")

# Main content
if st.session_state.graph is None:
    # Welcome screen
    st.info("👈 Enter a repository path or URL in the sidebar to get started!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔍 Auto-Detection")
        st.write("Automatically detects Maven, Gradle, Node.js, and Python projects")
    
    with col2:
        st.markdown("### 📊 Dependency Analysis")
        st.write("Build dependency graphs, analyze impacts, and get recommendations")
    
    with col3:
        st.markdown("### 🤖 AI-Powered")
        st.write("Ask questions in natural language using Ollama LLM")
    
    st.divider()
    
    st.markdown("### 📝 Example Repositories")
    
    examples = [
        ("Apache Commons Lang", "https://github.com/apache/commons-lang"),
        ("Spring Boot", "https://github.com/spring-projects/spring-boot"),
        ("JUnit 5", "https://github.com/junit-team/junit5"),
    ]
    
    for name, url in examples:
        if st.button(f"Try: {name}", key=url):
            result = scan_repository(url)
            if "error" in result:
                st.error(f"❌ {result['error']}")
            else:
                st.rerun()

else:
    # Tabs for different features
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview",
        "🔗 Class Dependencies",
        "💻 Runtime Analysis", 
        "🔍 Graph View", 
        "🔎 Impact Analysis", 
        "💡 Recommendations", 
        "🤖 AI Chat"
    ])
    
    with tab1:
        st.header("Project Overview")
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{st.session_state.project_name}</div>
                <div class="stat-label">Project</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{st.session_state.ecosystem or 'N/A'}</div>
                <div class="stat-label">Ecosystem</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{len(st.session_state.graph.get('nodes', []))}</div>
                <div class="stat-label">Dependencies</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-number">{len(st.session_state.graph.get('edges', []))}</div>
                <div class="stat-label">Relationships</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Dependencies list
        st.subheader("📦 All Dependencies")
        
        nodes = st.session_state.graph.get("nodes", [])
        if nodes:
            # Create a table
            deps_data = []
            for node in nodes:
                deps_data.append({
                    "Artifact": node.get("id", "N/A"),
                    "Type": node.get("type", "N/A"),
                    "Module": node.get("module", "N/A")
                })
            
            st.dataframe(deps_data, use_container_width=True, height=400)
        else:
            st.info("No dependencies found.")
        
        # Download SBOM
        st.divider()
        st.subheader("📄 Export SBOM")
        
        if st.button("Generate SBOM", type="primary"):
            sbom = generate_minimal_sbom(st.session_state.graph, st.session_state.project_name)
            st.json(sbom)
            
            import json
            st.download_button(
                label="⬇️ Download SBOM (JSON)",
                data=json.dumps(sbom, indent=2),
                file_name=f"{st.session_state.project_name}_sbom.json",
                mime="application/json"
            )
    
    # Tab 2: AST Analysis (Full Code Insights)
    with tab2:
        st.header("🌳 AST Code Analysis")
        st.write("**Complete AST-based code analysis** - Full parse tree with all details")
        
        if "ast_analysis" not in st.session_state or not st.session_state.ast_analysis:
            st.info("👈 Scan a repository first to see full AST analysis")
        else:
            ast_data = st.session_state.ast_analysis
            
            # Overview Metrics
            st.subheader("📊 Code Metrics")
            
            metrics = ast_data.get('metrics', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Classes", ast_data.get('total_classes', 0))
            with col2:
                st.metric("Total Files", ast_data.get('total_files', 0))
            with col3:
                st.metric("Total Methods", metrics.get('total_methods', 0))
            with col4:
                st.metric("Total Fields", metrics.get('total_fields', 0))
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_methods = metrics.get('avg_methods_per_class', 0)
                st.metric("Avg Methods/Class", f"{avg_methods:.1f}")
            with col2:
                avg_fields = metrics.get('avg_fields_per_class', 0)
                st.metric("Avg Fields/Class", f"{avg_fields:.1f}")
            with col3:
                st.metric("Public Classes", metrics.get('public_classes', 0))
            with col4:
                st.metric("Annotated Classes", metrics.get('annotated_classes', 0))
            
            st.divider()
            
            # Most Coupled Classes
            st.subheader("⚠️ Most Coupled Classes")
            st.write("Classes with highest number of dependencies (hardest to refactor)")
            
            most_coupled = metrics.get('most_coupled_classes', [])
            if most_coupled:
                for i, (class_name, dep_count) in enumerate(most_coupled[:10], 1):
                    simple_name = class_name.split('.')[-1]
                    package = '.'.join(class_name.split('.')[:-1])
                    
                    color = "🔴" if dep_count > 15 else "🟡" if dep_count > 8 else "🟢"
                    st.write(f"{color} **{i}. {simple_name}** ({package}) - {dep_count} dependencies")
            else:
                st.info("No coupling data available")
            
            st.divider()
            
            # Circular Dependencies
            st.subheader("🔄 Circular Dependencies")
            
            circular = ast_data.get('circular_dependencies', [])
            if circular:
                st.warning(f"Found {len(circular)} circular dependency chain(s)!")
                
                for i, cycle in enumerate(circular[:10], 1):
                    cycle_names = " → ".join([c.split('.')[-1] for c in cycle])
                    st.error(f"**Cycle {i}:** {cycle_names}")
                    
                    with st.expander(f"View full chain {i}"):
                        st.code(" → ".join(cycle))
            else:
                st.success("✅ No circular dependencies found!")
            
            st.divider()
            
            # Detailed Class Browser
            st.subheader("🔍 Class Explorer")
            
            classes = ast_data.get('classes', [])
            if classes:
                # Convert to simple format for selection
                class_names = [cls.full_name for cls in classes]
                selected_class_name = st.selectbox(
                    "Select a class to inspect:",
                    options=sorted(class_names)
                )
                
                if selected_class_name:
                    # Find the class
                    selected_class = next((cls for cls in classes if cls.full_name == selected_class_name), None)
                    
                    if selected_class:
                        st.write(f"### {selected_class.name}")
                        st.write(f"**Package:** `{selected_class.package}`")
                        st.write(f"**File:** {selected_class.file_path}")
                        
                        # Modifiers
                        if selected_class.modifiers:
                            st.write(f"**Modifiers:** {', '.join(selected_class.modifiers)}")
                        
                        # Annotations
                        if selected_class.annotations:
                            st.write(f"**Annotations:** {', '.join(selected_class.annotations)}")
                        
                        # Inheritance
                        if selected_class.extends:
                            st.write(f"**Extends:** `{selected_class.extends}`")
                        
                        if selected_class.implements:
                            st.write(f"**Implements:** {', '.join([f'`{i}`' for i in selected_class.implements])}")
                        
                        # Fields
                        if selected_class.fields:
                            st.write(f"**Fields ({len(selected_class.fields)}):**")
                            for field in selected_class.fields[:20]:  # Limit display
                                visibility = "🔒" if "private" in field.modifiers else "🔓" if "public" in field.modifiers else "🔐"
                                annot_str = f" {', '.join(field.annotations)}" if field.annotations else ""
                                st.write(f"  {visibility} `{field.type} {field.name}`{annot_str}")
                        
                        # Methods
                        if selected_class.methods:
                            st.write(f"**Methods ({len(selected_class.methods)}):**")
                            for method in selected_class.methods[:20]:  # Limit display
                                visibility = "🔒" if "private" in method.modifiers else "🔓" if "public" in method.modifiers else "🔐"
                                params = ", ".join([f"{p['type']} {p['name']}" for p in method.parameters])
                                return_type = method.return_type or "void"
                                annot_str = f" {', '.join(method.annotations)}" if method.annotations else ""
                                st.write(f"  {visibility} `{return_type} {method.name}({params})`{annot_str}")
                        
                        # Dependencies
                        if selected_class.dependencies:
                            st.write(f"**Dependencies ({len(selected_class.dependencies)}):**")
                            st.write(", ".join([f"`{dep}`" for dep in sorted(selected_class.dependencies)[:30]]))
            
            st.divider()
            
            # Errors
            errors = ast_data.get('errors', [])
            if errors:
                with st.expander(f"⚠️ Parsing Errors ({len(errors)})"):
                    for error in errors[:20]:
                        st.error(f"**{error['file']}**: {error['error']}")
    
    # Tab 3: Legacy Class Dependencies
    with tab2:
        st.header("� Internal Class Dependencies")
        st.write("**Service decomposition analysis** - Which classes depend on each other")
        
        if st.session_state.class_dependencies:
            class_data = st.session_state.class_dependencies
            stats = class_data.get("stats", {})
            
            # Summary stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Classes", stats.get("total_classes", 0))
            with col2:
                st.metric("Total Packages", stats.get("total_packages", 0))
            with col3:
                st.metric("Class Dependencies", stats.get("total_dependencies", 0))
            with col4:
                avg_deps = stats.get("average_dependencies", 0)
                st.metric("Avg Dependencies/Class", f"{avg_deps:.1f}")
            
            st.divider()
            
            # Data Coupling Summary
            st.subheader("📊 Data Coupling Analysis")
            st.write("Attribute-level dependencies and encapsulation quality")
            
            all_classes_data = class_data.get("classes", [])
            
            # Calculate data coupling metrics
            total_attributes = sum(cls.get('attribute_count', 0) for cls in all_classes_data)
            classes_with_getters = sum(1 for cls in all_classes_data 
                                       if any(a['access_type'] == 'getter' for a in cls.get('attribute_access', [])))
            classes_with_direct_access = sum(1 for cls in all_classes_data 
                                             if any(a['access_type'] == 'direct' for a in cls.get('attribute_access', [])))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Attributes", total_attributes)
            with col2:
                st.metric("Classes Using Getters", classes_with_getters)
                st.caption("✅ Good encapsulation")
            with col3:
                st.metric("Direct Field Access", classes_with_direct_access)
                if classes_with_direct_access > 0:
                    st.caption("⚠️ Encapsulation violations")
                else:
                    st.caption("✅ No violations")
            
            st.divider()
            
            # Most Coupled Classes (Refactoring Priority)
            st.subheader("⚠️ Most Coupled Classes (High Priority for Refactoring)")
            st.write("These classes have the most dependencies - hardest to extract/refactor")
            
            most_coupled = stats.get("most_coupled", [])
            if most_coupled:
                for i, item in enumerate(most_coupled[:10], 1):
                    class_name = item['class'].split('.')[-1]
                    package = '.'.join(item['class'].split('.')[:-1])
                    dep_count = item['dependency_count']
                    
                    color = "🔴" if dep_count > 10 else "🟡" if dep_count > 5 else "🟢"
                    st.write(f"{color} **{i}. {class_name}** ({package}) - {dep_count} dependencies")
            else:
                st.info("No coupling data available")
            
            st.divider()
            
            # Circular Dependencies (Breaking Changes)
            st.subheader("🔄 Circular Dependencies")
            st.write("These classes depend on each other - need refactoring to break cycles")
            
            circular = stats.get("circular_dependencies", [])
            if circular:
                st.warning(f"Found {len(circular)} circular dependency chain(s)!")
                
                for i, cycle in enumerate(circular[:5], 1):
                    cycle_str = " → ".join([c.split('.')[-1] for c in cycle])
                    st.error(f"**Cycle {i}:** {cycle_str}")
                    
                    with st.expander(f"View full chain {i}"):
                        st.code(" → ".join(cycle))
            else:
                st.success("✅ No circular dependencies found!")
            
            st.divider()
            
            # Package Coupling
            st.subheader("📦 Package Coupling")
            st.write("Classes grouped by package")
            
            packages = class_data.get("packages", {})
            if packages:
                package_stats = [(pkg, len(classes)) for pkg, classes in packages.items()]
                package_stats.sort(key=lambda x: x[1], reverse=True)
                
                st.bar_chart({pkg: count for pkg, count in package_stats[:15]}, height=300)
                
                # Show package details
                selected_package = st.selectbox(
                    "Select package to inspect:",
                    options=[pkg for pkg, _ in package_stats]
                )
                
                if selected_package:
                    classes_in_pkg = packages[selected_package]
                    st.write(f"**{len(classes_in_pkg)} classes in `{selected_package}`:**")
                    st.write(", ".join(classes_in_pkg))
            else:
                st.info("No package data available")
            
            st.divider()
            
            # Class Dependency Explorer
            st.subheader("🔍 Class Dependency Explorer")
            st.write("Explore dependencies for a specific class")
            
            all_classes = class_data.get("classes", [])
            class_names = [cls['full_name'] for cls in all_classes]
            
            selected_class = st.selectbox(
                "Select a class:",
                options=class_names if class_names else ["No classes found"]
            )
            
            if selected_class and selected_class != "No classes found":
                # Find the class
                class_info = next((cls for cls in all_classes if cls['full_name'] == selected_class), None)
                
                if class_info:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Package:** `{class_info['package']}`")
                        st.write(f"**File:** `{class_info['file']}`")
                        
                        if class_info.get('extends'):
                            st.write(f"**Extends:** `{class_info['extends']}`")
                        
                        if class_info.get('implements'):
                            st.write(f"**Implements:** {', '.join([f'`{i}`' for i in class_info['implements']])}")
                    
                    with col2:
                        st.metric("Dependencies", class_info['dependency_count'])
                        st.metric("Attributes", class_info.get('attribute_count', 0))
                    
                    st.divider()
                    
                    # Show attributes
                    if class_info.get('attributes'):
                        st.subheader("📋 Attributes (Fields):")
                        
                        for attr in class_info['attributes']:
                            visibility_icon = {
                                'public': '🟢',
                                'private': '🔴',
                                'protected': '🟡',
                                'package': '⚪'
                            }.get(attr['visibility'], '⚪')
                            
                            annotations = f" {', '.join(['@' + a for a in attr['annotations']])}" if attr.get('annotations') else ""
                            
                            st.code(f"{visibility_icon} {attr['visibility']} {attr['type']} {attr['name']}{annotations}", language='java')
                    else:
                        st.info("No attributes found")
                    
                    st.divider()
                    
                    # Show attribute access patterns
                    if class_info.get('attribute_access'):
                        st.subheader("🔗 Attribute Access (Data Coupling):")
                        st.write("This class accesses attributes/data from other classes:")
                        
                        # Group by access type
                        getters = [a for a in class_info['attribute_access'] if a['access_type'] == 'getter']
                        setters = [a for a in class_info['attribute_access'] if a['access_type'] == 'setter']
                        direct = [a for a in class_info['attribute_access'] if a['access_type'] == 'direct']
                        
                        if getters:
                            with st.expander(f"✅ Getter Calls ({len(getters)})"):
                                for acc in getters[:20]:
                                    st.write(f"- `{acc['target_class']}.{acc['method']}()` → gets `{acc['attribute']}`")
                        
                        if setters:
                            with st.expander(f"✏️ Setter Calls ({len(setters)})"):
                                for acc in setters[:20]:
                                    st.write(f"- `{acc['target_class']}.{acc['method']}()` → sets `{acc['attribute']}`")
                        
                        if direct:
                            with st.expander(f"⚠️ Direct Field Access ({len(direct)}) - Encapsulation Violation"):
                                for acc in direct[:20]:
                                    st.write(f"- `{acc['target_class']}.{acc['attribute']}` (direct access)")
                    
                    st.divider()
                    
                    # Show dependencies
                    if class_info.get('dependencies'):
                        st.subheader("Dependencies:")
                        for dep in class_info['dependencies']:
                            st.write(f"- `{dep}`")
                    else:
                        st.success("✅ No dependencies - isolated class!")
                    
                    # Show methods
                    if class_info.get('methods'):
                        with st.expander("View Methods"):
                            for method in class_info['methods']:
                                st.code(method, language='java')
            
            st.divider()
            
            # Service Decomposition Suggestions
            st.subheader("🎯 Service Decomposition Suggestions")
            st.write("Candidate classes for splitting into microservices")
            
            isolated = stats.get("isolated_classes", [])
            if isolated:
                st.success(f"Found {len(isolated)} isolated class(es) - easy to extract!")
                with st.expander(f"View {len(isolated)} isolated classes"):
                    for cls in isolated[:20]:
                        st.write(f"- `{cls}`")
            else:
                st.info("No isolated classes found")
            
            # Suggest service boundaries by package
            if packages:
                st.write("**Suggested service boundaries (by package):**")
                for pkg, classes in list(packages.items())[:10]:
                    if len(classes) > 3:  # Only packages with multiple classes
                        st.write(f"📦 **{pkg}** ({len(classes)} classes) → Candidate for microservice")
        
        else:
            st.info("No class dependency analysis available. Run a repository scan to analyze internal dependencies.")
    
    with tab3:
        st.header("�💻 Runtime Dependency Analysis")
        st.write("**Static code analysis** - What your code actually uses at runtime")
        
        if st.session_state.code_analysis:
            code_data = st.session_state.code_analysis
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Java Files Analyzed", code_data.get("total_files", 0))
            with col2:
                st.metric("External Libraries Detected", len(code_data.get("libraries", {})))
            with col3:
                st.metric("API Calls Found", code_data.get("api_call_count", 0))
            
            st.divider()
            
            # Hot Dependencies - Most Used Libraries
            st.subheader("🔥 Most Used Dependencies (by file count)")
            
            hot_deps = code_data.get("hot_dependencies", [])
            if hot_deps:
                for i, dep in enumerate(hot_deps[:10], 1):
                    with st.expander(f"{i}. **{dep['library']}** - Used in {dep['file_count']} files"):
                        st.write(f"📦 **Import count:** {dep['import_count']}")
                        st.write(f"📝 **Classes used:** {', '.join(dep['classes'][:20])}")
                        
                        if len(dep['classes']) > 20:
                            st.caption(f"...and {len(dep['classes']) - 20} more classes")
            else:
                st.info("No library usage detected")
            
            st.divider()
            
            # API Calls Detection
            st.subheader("🌐 External API Calls")
            
            api_calls = code_data.get("api_calls", [])
            if api_calls:
                st.write(f"Found **{len(api_calls)} API call(s)** in your code:")
                
                api_df = []
                for call in api_calls[:50]:  # Show first 50
                    api_df.append({
                        "Client Type": call.get("client_type", "unknown"),
                        "HTTP Method": call.get("method", "unknown"),
                        "Endpoint": call.get("endpoint", "unknown")
                    })
                
                st.dataframe(api_df, use_container_width=True)
                
                if len(api_calls) > 50:
                    st.caption(f"Showing first 50 of {len(api_calls)} API calls")
            else:
                st.info("No external API calls detected")
            
            st.divider()
            
            # Library Breakdown
            st.subheader("📚 Library Usage Details")
            
            libraries = code_data.get("libraries", {})
            if libraries:
                lib_chart_data = []
                for lib, stats in sorted(libraries.items(), key=lambda x: x[1]['file_count'], reverse=True)[:15]:
                    lib_chart_data.append({
                        "Library": lib,
                        "Files": stats['file_count'],
                        "Imports": stats['import_count']
                    })
                
                st.bar_chart(lib_chart_data, x="Library", y="Files", height=300)
                
                # Detailed table
                st.dataframe(lib_chart_data, use_container_width=True)
            else:
                st.info("No library usage data available")
            
            st.divider()
            
            # Impact Analysis Helper
            st.subheader("⚠️ Migration Impact Preview")
            st.write("**What breaks if you remove/replace a library?**")
            
            selected_lib = st.selectbox(
                "Select a library to analyze:",
                options=list(libraries.keys()) if libraries else ["No libraries found"]
            )
            
            if selected_lib and selected_lib != "No libraries found":
                lib_stats = libraries[selected_lib]
                st.warning(f"""
                **Impact of removing `{selected_lib}`:**
                
                - 🗂️ **{lib_stats['file_count']} files** would need refactoring
                - 📦 **{lib_stats['import_count']} import statements** would break
                - 🔧 **{len(lib_stats['classes'])} classes** would need replacement
                
                **Classes to replace:** {', '.join(lib_stats['classes'][:10])}
                {f'...and {len(lib_stats["classes"]) - 10} more' if len(lib_stats['classes']) > 10 else ''}
                """)
        else:
            st.info("No runtime analysis available. Run a repository scan to see code-level dependencies.")
    
    with tab4:
        st.header("Dependency Graph Visualization")
        st.write("Interactive graph view of your dependencies")
        
        # Configuration options
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.subheader("⚙️ Display Options")
            show_modules = st.checkbox("Show Modules", value=True)
            show_artifacts = st.checkbox("Show Artifacts", value=True)
            show_classes = st.checkbox("Show Class Dependencies", value=False, 
                                       help="Display internal class-to-class dependencies")
            layout = st.selectbox(
                "Layout",
                ["hierarchical", "force", "circular"],
                index=0
            )
        
        with col1:
            if st.button("🔄 Refresh Graph", type="primary"):
                st.rerun()
            
            # Build graph visualization
            nodes_viz = []
            edges_viz = []
            
            graph_data = st.session_state.graph
            
            for node in graph_data.get("nodes", []):
                node_id = node.get("id", "")
                node_type = node.get("type", "")
                
                # Filter based on user preference
                if node_type == "module" and not show_modules:
                    continue
                if node_type == "artifact" and not show_artifacts:
                    continue
                
                # Color and size based on type
                if node_type == "module":
                    color = "#1f77b4"  # Blue for modules
                    size = 30
                    label = node_id.replace("module:", "")
                else:
                    color = "#ff7f0e"  # Orange for artifacts
                    size = 20
                    # Shorten artifact labels
                    label = node_id.replace("artifact:", "")
                    parts = label.split(":")
                    if len(parts) >= 2:
                        label = f"{parts[1]}\n{parts[2] if len(parts) > 2 else ''}"  # artifact name + version
                
                nodes_viz.append(
                    Node(
                        id=node_id,
                        label=label,
                        size=size,
                        color=color,
                        shape="dot" if node_type == "artifact" else "box"
                    )
                )
            
            for edge in graph_data.get("edges", []):
                edge_from = edge.get("from", "")
                edge_to = edge.get("to", "")
                
                # Only add edge if both nodes are included
                from_included = any(n.id == edge_from for n in nodes_viz)
                to_included = any(n.id == edge_to for n in nodes_viz)
                
                if from_included and to_included:
                    edges_viz.append(
                        Edge(
                            source=edge_from,
                            target=edge_to,
                            color="#888",
                            width=1
                        )
                    )
            
            # Add class dependencies if enabled
            if show_classes and st.session_state.class_dependencies:
                class_data = st.session_state.class_dependencies
                
                # Add class nodes
                for cls in class_data.get("classes", []):
                    class_name = cls['full_name']
                    simple_name = cls['name']
                    dep_count = cls['dependency_count']
                    
                    # Color based on coupling level
                    if dep_count > 10:
                        color = "#d62728"  # Red - highly coupled
                    elif dep_count > 5:
                        color = "#ff7f0e"  # Orange - moderately coupled
                    else:
                        color = "#2ca02c"  # Green - loosely coupled
                    
                    nodes_viz.append(
                        Node(
                            id=f"class:{class_name}",
                            label=simple_name,
                            size=15 + (dep_count * 2),  # Size based on coupling
                            color=color,
                            shape="ellipse",
                            title=f"{class_name}\nDependencies: {dep_count}"
                        )
                    )
                
                # Add class dependency edges
                for edge in class_data.get("edges", []):
                    source_class = edge['from']
                    target_class = edge['to']
                    
                    edges_viz.append(
                        Edge(
                            source=f"class:{source_class}",
                            target=f"class:{target_class}",
                            color="#9467bd",  # Purple for class dependencies
                            width=1,
                            dashes=True  # Dashed lines to distinguish from artifact dependencies
                        )
                    )
            
            # Configure graph layout
            config = Config(
                width="100%",
                height=600,
                directed=True,
                physics=layout == "force",
                hierarchical=layout == "hierarchical",
                layout={
                    "hierarchical": {
                        "enabled": layout == "hierarchical",
                        "direction": "LR",
                        "sortMethod": "directed"
                    }
                } if layout == "hierarchical" else {},
            )
            
            # Display graph
            if nodes_viz:
                st.info(f"📊 Displaying {len(nodes_viz)} nodes and {len(edges_viz)} edges")
                agraph(nodes=nodes_viz, edges=edges_viz, config=config)
            else:
                st.warning("No nodes to display. Enable at least one node type.")
            
            # Legend
            st.divider()
            st.subheader("📌 Legend")
            lcol1, lcol2 = st.columns(2)
            with lcol1:
                st.markdown("🟦 **Blue Boxes** = Modules")
            with lcol2:
                st.markdown("🟧 **Orange Dots** = Artifacts")
            
            # Neo4j Export Section
            st.divider()
            st.subheader("🗄️ Export to Neo4j")
            st.write("Generate Cypher queries to import this graph into Neo4j Database")
            
            col_neo1, col_neo2 = st.columns([2, 1])
            
            with col_neo1:
                if st.button("🔧 Generate Neo4j Cypher Script", type="primary"):
                    cypher_script = generate_neo4j_cypher(st.session_state.graph, st.session_state.project_name)
                    st.session_state.neo4j_script = cypher_script
                    st.success("✅ Cypher script generated!")
            
            with col_neo2:
                if "neo4j_script" in st.session_state:
                    st.download_button(
                        label="⬇️ Download .cypher",
                        data=st.session_state.neo4j_script,
                        file_name=f"{st.session_state.project_name}_neo4j_import.cypher",
                        mime="text/plain"
                    )
            
            # Show preview and instructions
            if "neo4j_script" in st.session_state:
                with st.expander("📝 View Cypher Script Preview"):
                    st.code(st.session_state.neo4j_script[:1000] + "\n..." if len(st.session_state.neo4j_script) > 1000 else st.session_state.neo4j_script, language="cypher")
                
                with st.expander("📖 How to Import into Neo4j"):
                    st.markdown("""
                    ### Option 1: Neo4j Desktop
                    1. Open **Neo4j Desktop**
                    2. Start your database
                    3. Click **Open Browser**
                    4. Copy and paste the Cypher script into the query editor
                    5. Click **Run** (play button)
                    
                    ### Option 2: Neo4j Browser
                    1. Open Neo4j Browser at `http://localhost:7474`
                    2. Login with your credentials
                    3. Paste the downloaded `.cypher` file content
                    4. Execute the queries
                    
                    ### Option 3: Cypher Shell (CLI)
                    ```bash
                    cat {0}_neo4j_import.cypher | cypher-shell -u neo4j -p your-password
                    ```
                    
                    ### Option 4: Neo4j Aura (Cloud)
                    1. Login to **Neo4j Aura Console**
                    2. Open your database
                    3. Go to **Query** tab
                    4. Paste and run the script
                    
                    ### Useful Neo4j Queries After Import:
                    ```cypher
                    // View all modules
                    MATCH (m:module) RETURN m LIMIT 25;
                    
                    // View dependency tree
                    MATCH path = (m:module)-[:DEPENDS_ON*]->(a:artifact)
                    RETURN path LIMIT 50;
                    
                    // Find modules with most dependencies
                    MATCH (m:module)-[:DEPENDS_ON]->(a:artifact)
                    RETURN m.name, count(a) as dep_count
                    ORDER BY dep_count DESC;
                    
                    // Find artifacts used by multiple modules
                    MATCH (m:module)-[:DEPENDS_ON]->(a:artifact)
                    WITH a, collect(m.name) as modules, count(m) as usage_count
                    WHERE usage_count > 1
                    RETURN a.coordinate, modules, usage_count
                    ORDER BY usage_count DESC;
                    ```
                    """.format(st.session_state.project_name))
    
    with tab5:
        st.header("Impact Analysis")
        st.write("Analyze which modules depend on a specific artifact")
        
        artifact_coord = st.text_input(
            "Artifact Coordinate",
            placeholder="group:artifact:version (e.g., org.springframework:spring-core:5.3.0)",
            help="Enter the full artifact coordinate to analyze"
        )
        
        if st.button("Analyze Impact", type="primary"):
            if artifact_coord:
                with st.spinner("Analyzing impact..."):
                    result = impact_summary(st.session_state.graph, artifact_coord)
                    
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        st.success("✅ Impact Analysis Complete")
                        
                        st.subheader("Results")
                        st.json(result)
                        
                        affected = result.get("affected_modules", [])
                        if affected:
                            st.warning(f"⚠️ This artifact affects {len(affected)} module(s)")
                            for mod in affected:
                                st.write(f"- {mod}")
                        else:
                            st.info("ℹ️ No modules directly depend on this artifact")
            else:
                st.warning("Please enter an artifact coordinate")
    
    with tab6:
        st.header("💡 Recommendations")
        st.write("Get version upgrade suggestions for artifacts")
        
        if not AGENT_AVAILABLE:
            st.error("❌ AI Agent not available")
        else:
            rec_artifact = st.text_input(
                "Artifact to Upgrade",
                placeholder="group:artifact:version",
                key="rec_artifact"
            )
            
            policy = st.selectbox(
                "Upgrade Policy",
                ["latest_patch", "latest_minor", "latest_major"],
                help="Choose the upgrade strategy"
            )
            
            if st.button("💡 Get Recommendation", type="primary"):
                if rec_artifact:
                    if init_agent():
                        with st.spinner("🤖 Agent is generating recommendations..."):
                            response = st.session_state.agent.run(
                                f"Recommend upgrade for artifact: {rec_artifact} using policy: {policy}",
                                context={"action": "artifact_recommendation", "artifact": rec_artifact, "policy": policy}
                            )
                            st.write(response)
                    else:
                        st.error("Failed to initialize agent")
                else:
                    st.warning("Please enter an artifact coordinate")
    
    with tab7:
        st.header("🤖 AI Assistant")
        
        if not AGENT_AVAILABLE:
            st.error("❌ AI Agent not available. Ollama may not be running or configured.")
        else:
            # Show MCP status
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("💬 Ask questions about your dependencies in natural language!")
            with col2:
                if st.session_state.mcp_client:
                    st.success("🔌 MCP Connected")
                else:
                    st.warning("⚠️ No MCP client")
            
            # Initialize agent
            if init_agent():
                
                # Chat interface
                chat_container = st.container()
                
                with chat_container:
                    # Display chat history
                    for msg in st.session_state.chat_history:
                        with st.chat_message(msg["role"]):
                            st.write(msg["content"])
                
                # User input
                user_query = st.chat_input("Ask a question about dependencies...")
                
                if user_query:
                    # Add user message
                    st.session_state.chat_history.append({"role": "user", "content": user_query})
                    
                    with st.chat_message("user"):
                        st.write(user_query)
                    
                    # Get agent response
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            response = st.session_state.agent.chat(user_query)
                            st.write(response)
                    
                    # Add assistant message
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # Quick questions
                st.divider()
                st.subheader("Quick Questions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📋 List all dependencies"):
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": "List all dependencies in this project"
                        })
                        st.rerun()
                    
                    if st.button("🔐 Check for vulnerabilities"):
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": "Are there any vulnerable or outdated dependencies?"
                        })
                        st.rerun()
                
                with col2:
                    if st.button("📊 Generate SBOM"):
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": "Generate an SBOM for this project"
                        })
                        st.rerun()
                    
                    if st.button("🔄 Suggest upgrades"):
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": "Recommend safe dependency upgrades"
                        })
                        st.rerun()
                
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_history = []
                    if st.session_state.agent:
                        st.session_state.agent.conversation_history = []
                    st.rerun()

# Footer
st.divider()
st.caption("Built with ❤️ using Streamlit | Dependency Analyzer v1.0")
