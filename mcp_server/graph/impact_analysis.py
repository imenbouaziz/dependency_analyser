
"""
impact_analysis.py
Very basic impact utilities on top of the simple graph.

Capabilities:
- find_modules_using(artifact_coord): list modules that directly depend on an artifact
- explain_paths(module, artifact): show direct edges (basic) from module -> artifact
  (No full transitive resolution here — keep it simple for MVP.)

Graph input expected:
{
  "nodes": [...],
  "edges": [{"from": "...", "to": "...", "meta": {...}}, ...],
  "index": {"modules": {...}, "artifacts": {...}}
}
"""

from __future__ import annotations
from typing import Dict, List

def find_modules_using(graph: Dict, artifact_coord: str) -> List[str]:
    """
    Return module IDs that have a direct 'depends_on' edge to the given artifact coord.

    Args:
        graph: graph dict from graph_builder
        artifact_coord: "group:artifact:version" (version may be empty)

    Returns:
        List of "module:<name>" strings
    """
    target = f"artifact:{artifact_coord}"
    used_by = []
    for e in graph.get("edges", []):
        if e.get("to") == target and e.get("meta", {}).get("relation") == "depends_on":
            src = e.get("from", "")
            if src.startswith("module:"):
                used_by.append(src)
    # Unique & sorted for deterministic output
    return sorted(set(used_by))

def explain_paths(graph: Dict, module_name: str, artifact_coord: str) -> List[Dict]:
    """
    Very basic path explanation: returns a list of direct edges if any.
    (No transitive pathfinding here; only direct depends_on edges.)

    Args:
        graph: graph dict
        module_name: module name (not the 'module:<name>' id)
        artifact_coord: "group:artifact:version"

    Returns:
        [
          {"from": "module:<name>", "to": "artifact:<coord>", "meta": {"relation":"depends_on"}}
        ]
    """
    mod_id = graph.get("index", {}).get("modules", {}).get(module_name)
    art_id = graph.get("index", {}).get("artifacts", {}).get(artifact_coord)
    if not mod_id or not art_id:
        return []

    paths = []
    for e in graph.get("edges", []):
        if e.get("from") == mod_id and e.get("to") == art_id:
            paths.append(e)
    return paths

def impact_summary(graph: Dict, artifact_coord: str) -> Dict:
    """
    Produce a small impact summary for a specific artifact.

    Returns:
        {
          "artifact": "<coord>",
          "used_by_modules": ["module:<a>", "module:<b>"],
          "count": N
        }
    """
    modules = find_modules_using(graph, artifact_coord)
    return {
        "artifact": artifact_coord,
        "used_by_modules": modules,
        "count": len(modules),
    }
