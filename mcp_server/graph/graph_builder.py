
"""
graph_builder.py
Builds a very simple in-memory dependency graph from parsed modules.

Input shape expected (from your parsers):
[
  {
    "ecosystem": "maven" | "gradle",
    "module": "module-name",
    "dependencies": [
      { "group": "g", "artifact": "a", "version": "v", "scope"/"configuration": "...", ... }
    ],
    "source": "/abs/path/to/pom.xml|build.gradle"
  },
  ...
]

Output graph (LLM-friendly):
{
  "nodes": [
    {"id": "module:<name>", "type": "module", "meta": {...}},
    {"id": "artifact:<coord>", "type": "artifact", "meta": {...}},
  ],
  "edges": [
    {"from": "module:<name>", "to": "artifact:<coord>", "meta": {"relation": "depends_on"}}
  ],
  "index": {
    "modules": {"<name>": "module:<name>"},
    "artifacts": {"<coord>": "artifact:<coord>"}
  },
  "stats": { "module_count": X, "artifact_count": Y, "edge_count": Z }
}

Note:
- We store a very simple index for fast lookups.
- Coordinates:
  - Maven/Gradle: "group:artifact:version" (version may be empty)
"""

from __future__ import annotations
from typing import Dict, List, Tuple

def _artifact_coord_maven_gradle(group: str, artifact: str, version: str) -> str:
    """Create a canonical coordinate 'group:artifact:version' (version may be empty)."""
    group = (group or "").strip()
    artifact = (artifact or "").strip()
    version = (version or "").strip()
    return f"{group}:{artifact}:{version}"

def build_graph(parsed_modules: List[Dict]) -> Dict:
    """
    Build a unified dependency graph from a list of parsed module dicts.

    Args:
        parsed_modules: list of dicts from parse_maven_module / parse_gradle_module

    Returns:
        graph dict (nodes, edges, index, stats)
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    seen_nodes = set()

    index = {"modules": {}, "artifacts": {}}

    def add_node(node_id: str, ntype: str, meta: Dict):
        if node_id not in seen_nodes:
            nodes.append({"id": node_id, "type": ntype, "meta": meta})
            seen_nodes.add(node_id)

    for mod in parsed_modules:
        if not isinstance(mod, dict) or "module" not in mod or "dependencies" not in mod:
            # Skip malformed entries
            continue

        module_name = mod.get("module", "").strip()
        ecosystem = mod.get("ecosystem", "").strip() or "java"
        source = mod.get("source", "")

        mod_id = f"module:{module_name}"
        add_node(mod_id, "module", {"ecosystem": ecosystem, "source": source})
        index["modules"][module_name] = mod_id

        for dep in mod.get("dependencies", []):
            group = dep.get("group", "")
            artifact = dep.get("artifact", "")
            version = dep.get("version", "")
            coord = _artifact_coord_maven_gradle(group, artifact, version)
            art_id = f"artifact:{coord}"

            # Minimal meta copied for convenience
            meta = {}
            if "scope" in dep:
                meta["scope"] = dep["scope"]
            if "configuration" in dep:
                meta["configuration"] = dep["configuration"]

            add_node(art_id, "artifact", meta)
            index["artifacts"][coord] = art_id

            edges.append({
                "from": mod_id,
                "to": art_id,
                "meta": {"relation": "depends_on"}
            })

    stats = {
        "module_count": len(index["modules"]),
        "artifact_count": len(index["artifacts"]),
        "edge_count": len(edges),
    }

    return {"nodes": nodes, "edges": edges, "index": index, "stats": stats}
