
"""
maven_scanner.py
Java-only: Detect Maven projects and their modules.

This scanner:
- Detects the root Maven project by finding a pom.xml at the repo root
- Parses <modules> from the root POM (multi-module aggregator)
- Falls back to single-module if no <modules> exist
- Returns a clean, LLM-friendly structure

NOTE: We intentionally use ElementTree (XML) rather than regex for safety.
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from mcp_server.utils.filesystem import read_xml_safe, xml_text
from mcp_server.parsers.java_code_parser import scan_java_files, aggregate_dependency_usage
from mcp_server.parsers.class_dependency_parser import analyze_class_dependencies


def _detect_maven_root(root_path: str) -> Optional[str]:
    """Return the path to root pom.xml if present, else None."""
    pom = os.path.join(root_path, "pom.xml")
    return pom if os.path.isfile(pom) else None


def _extract_modules_from_pom(pom_path: str) -> List[str]:
    """
    Extract <module> entries from an aggregator pom.xml.

    <modules>
      <module>module-a</module>
      <module>module-b</module>
    </modules>

    Returns a list of directory names (as given in POM).
    """
    root = read_xml_safe(pom_path)
    if root is None:
        return []

    # Handle namespace
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag[root.tag.find("{")+1:root.tag.find("}")]
    
    ns = {"mvn": namespace} if namespace else {}
    
    # Find modules tag
    if namespace:
        modules_tag = root.find("mvn:modules", ns)
        module_tags = modules_tag.findall("mvn:module", ns) if modules_tag is not None else []
    else:
        modules_tag = root.find("modules")
        module_tags = modules_tag.findall("module") if modules_tag is not None else []

    names: List[str] = []
    for m in module_tags:
        if m.text:
            name = m.text.strip()
            if name:
                names.append(name)
    return names


def _detect_artifact_id(pom_path: str) -> str:
    """Try to get <artifactId> from pom.xml; fallback to folder name if missing."""
    root = read_xml_safe(pom_path)
    if root is None:
        return os.path.basename(os.path.dirname(pom_path))
    
    # Handle namespace
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag[root.tag.find("{")+1:root.tag.find("}")]
    
    if namespace:
        ns = {"mvn": namespace}
        aid_elem = root.find("mvn:artifactId", ns)
    else:
        aid_elem = root.find("artifactId")
    
    aid = (aid_elem.text or "").strip() if aid_elem is not None and aid_elem.text else ""
    return aid or os.path.basename(os.path.dirname(pom_path))


def scan_maven_repo(path: str) -> Dict:
    """
    Scan a Java repository to detect Maven modules.

    Args:
        path: Filesystem path to the repository root.

    Returns:
        {
          "ecosystem": "maven",
          "root": "<absolute path to root pom.xml>",
          "modules": [
              {"name": "<module-or-root-name>", "path": "<abs path to pom.xml>"}
          ],
          "summary": "human-readable summary string"
        }
        or
        {"error": "Reason"}  on failure.
    """
    # --- Validate path ---
    if not os.path.isdir(path):
        return {"error": f"Path not found: {path}"}
    path = os.path.abspath(path)

    # --- Detect Maven root (pom.xml at root) ---
    root_pom = _detect_maven_root(path)
    if not root_pom:
        return {"error": "No pom.xml found at repository root; not a Maven project."}

    # --- Multi-module detection ---
    modules = []
    module_names = _extract_modules_from_pom(root_pom)

    if module_names:
        # Multi-module aggregator POM
        for name in module_names:
            # Each <module> is typically a directory containing its own pom.xml
            mod_pom = os.path.join(path, name, "pom.xml")
            modules.append({
                "name": name,
                "path": os.path.abspath(mod_pom),
                # Optional: You could add "exists": os.path.isfile(mod_pom) for validation
            })
        summary = f"Maven multi-module project with {len(modules)} modules."
    else:
        # Single-module project (no <modules>)
        # Use artifactId when possible for a nicer display name
        name = _detect_artifact_id(root_pom)
        modules.append({"name": name, "path": os.path.abspath(root_pom)})
        summary = "Maven single-module project."

    return {
        "ecosystem": "maven",
        "root": os.path.abspath(root_pom),
        "modules": modules,
        "summary": summary,
    }


def scan_maven_repo_with_code_analysis(path: str, analyze_code: bool = True) -> Dict:
    """
    Enhanced scan that includes both pom.xml dependencies AND actual code usage.
    
    Args:
        path: Repository root path
        analyze_code: Whether to perform static code analysis (default: True)
    
    Returns:
        Same as scan_maven_repo, plus:
        {
            ...
            "code_analysis": {
                "total_files": 150,
                "libraries": {...},
                "hot_dependencies": [...]
            },
            "class_dependencies": {
                "classes": [...],
                "edges": [...],
                "stats": {...}
            }
        }
    """
    # First, do the standard Maven scan
    result = scan_maven_repo(path)
    
    if "error" in result:
        return result
    
    # Then, analyze Java source code if requested
    if analyze_code:
        # External library usage
        java_analyses = scan_java_files(path, max_files=1000)
        code_analysis = aggregate_dependency_usage(java_analyses)
        result["code_analysis"] = code_analysis
        
        # Internal class dependencies
        class_deps = analyze_class_dependencies(path)
        result["class_dependencies"] = class_deps
        
        result["summary"] += f" Code analysis: {code_analysis['total_files']} Java files, {class_deps['stats']['total_classes']} classes analyzed."
    
    return result


if __name__ == "__main__":
    # Lightweight manual test:
    repo = os.getcwd()  # or replace with a concrete path
    result = scan_maven_repo(repo)
    print(result)
