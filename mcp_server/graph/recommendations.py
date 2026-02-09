
"""
recommendations.py
Naive version bump recommendations for artifacts.

For MVP we:
- Parse semantic-like versions "MAJOR.MINOR.PATCH" (best effort).
- Provide simple policies: latest_patch, latest_minor, latest_major (simulated).
- Do NOT query any remote registries (offline).
- Return an LLM-friendly structure.

Later: integrate Maven Central / internal registries / CVE feeds / BOMs.
"""

from __future__ import annotations
import re
from typing import Dict

_VERSION_NUMS = re.compile(r"(\d+)\.(\d+)\.(\d+)")

def _parse_semver(v: str):
    """
    Best-effort parse: return (major, minor, patch); missing values treated as 0.
    """
    m = _VERSION_NUMS.search(v or "")
    if not m:
        # Handle '1.2' or '1'
        parts = [p for p in (v or "").split(".") if p.isdigit()]
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return major, minor, patch
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def _bump(v: str, level: str) -> str:
    """
    Bump version by level: 'patch'|'minor'|'major'
    If parsing fails, return the input as-is.
    """
    try:
        major, minor, patch = _parse_semver(v)
        if level == "patch":
            patch += 1
        elif level == "minor":
            minor += 1
            patch = 0
        elif level == "major":
            major += 1
            minor, patch = 0, 0
        return f"{major}.{minor}.{patch}"
    except Exception:
        return v or ""

def recommend_upgrade(artifact_coord: str, policy: str = "latest_patch") -> Dict:
    """
    Suggest a version bump based on a simple policy. PURELY HEURISTIC.

    Args:
        artifact_coord: "group:artifact:version" (version may be empty)
        policy: "latest_patch" | "latest_minor" | "latest_major"

    Returns:
        {
          "artifact": "...",
          "current": "x",
          "suggested": "y",
          "policy": policy,
          "notes": "string"
        }
    """
    parts = (artifact_coord or "").split(":")
    current = parts[-1] if len(parts) >= 3 else ""  # if version missing, this may be wrong/empty
    level = "patch" if policy == "latest_patch" else ("minor" if policy == "latest_minor" else "major")
    suggested = _bump(current, level)
    notes = "Heuristic bump; integrate real registry or BOM data for accuracy."
    return {
        "artifact": artifact_coord,
        "current": current,
        "suggested": suggested,
        "policy": policy,
        "notes": notes,
    }
