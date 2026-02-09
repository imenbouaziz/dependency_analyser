
"""
sbom_generator.py
Minimal CycloneDX-style SBOM generator (JSON) for the MVP.

This is intentionally simplified:
- Creates one 'application' component for the project.
- Adds components for each unique artifact found in the graph (group:artifact:version).
- Does not compute hashes, licenses, external references, or dependencies mapping.

Later improvements:
- Use official cyclonedx-python-lib to build spec-compliant SBOMs.
- Add licenses, supplier, hashes, dependency relationships, bomRef linking.
"""

from __future__ import annotations
import time
from typing import Dict, List

def _artifact_to_component(coord: str) -> Dict:
    """
    Convert 'group:artifact:version' to a CycloneDX-like component dict.
    """
    group, artifact, version = "", "", ""
    parts = (coord or "").split(":")
    if len(parts) >= 2:
        group, artifact = parts[0], parts[1]
    if len(parts) >= 3:
        version = parts[2]

    purl = ""
    # For Java/Maven artifacts, a simple purl template (best effort, not exact):
    # pkg:maven/{group}/{artifact}@{version}
    if group and artifact:
        purl = f"pkg:maven/{group}/{artifact}@{version}" if version else f"pkg:maven/{group}/{artifact}"

    name = f"{group}:{artifact}" if group else artifact

    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": purl,
        "vendor": group or None,
    }

def generate_minimal_sbom(graph: Dict, project_name: str = "java-project") -> Dict:
    """
    Create a minimal SBOM JSON-like structure (CycloneDX-inspired).

    Args:
        graph: graph dict from graph_builder
        project_name: name of the root application

    Returns:
        dict representing an SBOM
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Application/root component
    metadata = {
        "timestamp": ts,
        "component": {
            "type": "application",
            "name": project_name,
        }
    }

    # Collect unique artifact coordinates from graph index
    artifacts = sorted(set(graph.get("index", {}).get("artifacts", {}).keys()))
    components: List[Dict] = []
    for coord in artifacts:
        components.append(_artifact_to_component(coord))

    # Minimal CycloneDX-like SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": metadata,
        "components": components,
        # "dependencies": []   # You can add module->artifact relationships later
    }
    return sbom
