"""
prompts.py
System prompts and templates for the Dependency Analyzer Agent.
"""

SYSTEM_PROMPT = """You are an expert software dependency analyzer assistant. You help developers understand and manage their project dependencies.

You have access to the following tools to analyze dependency graphs:

1. **build_dependency_graph(parsed_modules)** - Build a dependency graph from parsed modules
2. **artifact_impact(artifact_coord)** - Find which modules use a specific artifact (format: "group:artifact:version")
3. **artifact_recommendation(artifact_coord, policy)** - Get version upgrade recommendations
4. **export_sbom(project_name)** - Export a CycloneDX SBOM

The repository has already been scanned and the dependency graph has been built.

**Your capabilities:**
- Analyze dependency relationships and impact
- Identify security vulnerabilities and outdated dependencies
- Recommend safe upgrade paths
- Explain dependency conflicts
- Generate SBOMs for compliance

**Guidelines:**
- Provide clear, actionable insights
- When analyzing impacts, explain the scope and risk
- For upgrade recommendations, consider backward compatibility
- Use artifact coordinates in the format "groupId:artifactId:version"
- Be concise but thorough

**Response Format:**
- Start with a brief summary
- Provide detailed analysis with specific artifacts
- Include actionable recommendations
- Use bullet points for clarity
"""

TOOL_INSTRUCTIONS = """
To use tools, structure your response as:

**Thought:** [Your reasoning about what information you need]
**Action:** [tool_name]
**Action Input:** [JSON parameters for the tool]

Then wait for the observation before continuing.

Example:
**Thought:** I need to find which modules depend on log4j to assess the impact.
**Action:** artifact_impact
**Action Input:** {"artifact_coord": "org.apache.logging.log4j:log4j-core:2.14.1"}
"""

QUERY_TEMPLATES = {
    "impact_analysis": """Analyze the impact of upgrading or removing the artifact: {artifact}

Consider:
1. Which modules directly depend on it?
2. How critical is this dependency?
3. What would break if we removed/changed it?
4. Are there alternative dependencies?
""",
    
    "vulnerability_check": """Check for known vulnerable dependencies in the project.

Focus on:
1. Outdated versions of security-critical libraries
2. Dependencies with known CVEs
3. Recommended upgrade paths
4. Priority ranking by severity
""",
    
    "upgrade_strategy": """Create a safe upgrade strategy for: {artifact}

Include:
1. Current version analysis
2. Latest stable version recommendation
3. Breaking changes to watch for
4. Testing strategy
5. Rollback plan
""",
    
    "dependency_conflicts": """Identify and resolve dependency conflicts in the project.

Analyze:
1. Version conflicts across modules
2. Transitive dependency issues
3. Scope conflicts (compile vs test)
4. Resolution recommendations
""",
    
    "sbom_generation": """Generate a Software Bill of Materials (SBOM) for: {project_name}

Purpose:
1. Compliance and auditing
2. License tracking
3. Security scanning integration
4. Supply chain transparency
"""
}

RESPONSE_TEMPLATES = {
    "impact_summary": """
## Impact Analysis: {artifact}

**Affected Modules:** {module_count}
- {module_list}

**Risk Level:** {risk_level}

**Recommendations:**
{recommendations}
""",
    
    "upgrade_recommendation": """
## Upgrade Recommendation: {artifact}

**Current Version:** {current_version}
**Recommended Version:** {recommended_version}
**Policy:** {policy}

**Changes:**
{changes}

**Action Items:**
{action_items}
""",
    
    "sbom_summary": """
## SBOM Generated: {project_name}

**Format:** CycloneDX JSON
**Components:** {component_count}
**Timestamp:** {timestamp}

**Summary:**
{summary}

SBOM can be used for:
- Security scanning tools
- License compliance checks
- Regulatory requirements (e.g., NTIA, Executive Order 14028)
"""
}

ERROR_MESSAGES = {
    "no_graph": "No dependency graph has been built yet. Please scan a repository first using the MCP server.",
    "invalid_artifact": "Invalid artifact coordinate format. Use 'groupId:artifactId:version' (e.g., 'org.springframework:spring-core:5.3.0')",
    "tool_error": "An error occurred while executing the tool: {error}",
    "parsing_error": "Failed to parse the tool output. Please try rephrasing your question.",
}

def format_artifact_list(artifacts: list) -> str:
    """Format a list of artifacts for display."""
    if not artifacts:
        return "None"
    return "\n".join(f"- {a}" for a in artifacts)

def format_module_list(modules: list) -> str:
    """Format a list of modules for display."""
    if not modules:
        return "None"
    return "\n".join(f"- {m}" for m in modules)

def create_impact_response(artifact: str, modules: list, risk_level: str = "Medium") -> str:
    """Create a formatted impact analysis response."""
    return RESPONSE_TEMPLATES["impact_summary"].format(
        artifact=artifact,
        module_count=len(modules),
        module_list=format_module_list(modules),
        risk_level=risk_level,
        recommendations="Review each affected module before making changes."
    )
