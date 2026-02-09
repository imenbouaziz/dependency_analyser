
"""
maven_parser.py
Basic Maven parser: extracts direct dependencies from a pom.xml using ElementTree.

⚠️ Scope & Limitations (by design, for simplicity):
- Parses ONLY direct dependencies declared under <dependencies>.
- Ignores <dependencyManagement>, profiles, properties interpolation, parents.
- Does not resolve versions inherited from BOMs or properties.
- Does not compute transitive dependencies.
- Returns a minimal, LLM-friendly JSON shape.

You can later swap this with:
- mvn -q dependency:tree -DoutputType=text|dot|json  (subprocess)
- Proper XML namespace handling and property resolution.
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from typing import Dict, List
from mcp_server.utils.filesystem import read_xml_safe, xml_text


def parse_maven_module(pom_path: str) -> Dict:
    """
    Parse a Maven pom.xml and extract direct dependencies.

    Args:
        pom_path: Absolute path to a pom.xml

    Returns:
        {
          "ecosystem": "maven",
          "module": "<artifactId or folder name>",
          "dependencies": [
            {
              "group": "g",
              "artifact": "a",
              "version": "v",       # may be empty if unspecified/inherited
              "scope": "compile|test|runtime|provided|system|",
              "optional": false
            },
            ...
          ],
          "summary": "human-readable"
        }
        or
        {"error": "..."} on failure.
    """
    if not os.path.isfile(pom_path):
        return {"error": f"pom.xml not found: {pom_path}"}

    root = read_xml_safe(pom_path)
    if root is None:
        return {"error": f"Failed to parse XML: {pom_path}"}

    # Extract namespace if present (Maven POMs often use http://maven.apache.org/POM/4.0.0)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag[root.tag.find("{")+1:root.tag.find("}")]
    
    ns = {"mvn": namespace} if namespace else {}
    
    def find_text(parent, tag):
        """Helper to find text with or without namespace"""
        if namespace:
            elem = parent.find(f"mvn:{tag}", ns)
        else:
            elem = parent.find(tag)
        return (elem.text or "").strip() if elem is not None and elem.text else ""

    # Determine a simple module name.
    # Prefer <artifactId>, fall back to directory name.
    artifact_id = find_text(root, "artifactId")
    module_name = artifact_id or os.path.basename(os.path.dirname(pom_path))

    deps: List[Dict] = []
    # Find <dependencies> / <dependency> (with namespace support)
    if namespace:
        deps_tag = root.find("mvn:dependencies", ns)
        dep_tags = deps_tag.findall("mvn:dependency", ns) if deps_tag is not None else []
    else:
        deps_tag = root.find("dependencies")
        dep_tags = deps_tag.findall("dependency") if deps_tag is not None else []
    
    for d in dep_tags:
        group = find_text(d, "groupId")
        artifact = find_text(d, "artifactId")
        version = find_text(d, "version")  # may be empty (managed elsewhere)
        scope = find_text(d, "scope") or "compile"  # Maven default is compile
        optional_txt = find_text(d, "optional")
        optional = (optional_txt.lower() == "true") if optional_txt else False

        if group and artifact:
            deps.append({
                "group": group,
                "artifact": artifact,
                "version": version,
                "scope": scope,
                "optional": optional,
            })

    summary = f"Maven module '{module_name}' with {len(deps)} direct dependencies."

    return {
        "ecosystem": "maven",
        "module": module_name,
        "dependencies": deps,
        "summary": summary,
        "source": os.path.abspath(pom_path),
    }


if __name__ == "__main__":
    # Quick manual test (run in a folder containing a pom.xml)
    here = os.getcwd()
    pom = os.path.join(here, "pom.xml")
    print(parse_maven_module(pom))
