
"""
gradle_scanner.py
Java-only: Detect Gradle projects and their modules.

This scanner:
- Detects Gradle projects via settings.gradle(.kts) OR single-module build.gradle(.kts)
- Parses include statements from settings to find subprojects
- Maps Gradle project paths (e.g., ':app', ':libs:core') to directories
- Falls back to single-module when no includes are present

NOTE: Gradle allows custom projectDir mappings in settings:
  project(":libs:core").projectDir = file("components/core")
This scanner assumes default mapping (path segments → directories).
If a derived directory lacks a build file, it tries a shallow search by last segment.
"""

from __future__ import annotations
import os
import re
from typing import Dict, List, Optional, Tuple


# --------------------------
# Helpers for settings parsing
# --------------------------

_INCLUDE_CALL_PATTERN = re.compile(
    r"""
    ^\s*include        # include keyword
    \s*\(?             # optional opening parenthesis (KTS style)
    (?P<args>.*?)      # capture all arguments inside
    \)?\s*$            # optional closing parenthesis and line end
    """,
    re.MULTILINE | re.VERBOSE,
)

_QUOTED_TOKEN_PATTERN = re.compile(
    r"""
    ['"]                # opening quote
    (?P<token>[^'"]+)   # token (no quotes inside)
    ['"]                # closing quote
    """,
    re.VERBOSE,
)


def _detect_settings_file(root: str) -> Optional[str]:
    """Return settings.gradle or settings.gradle.kts if present."""
    s1 = os.path.join(root, "settings.gradle")
    s2 = os.path.join(root, "settings.gradle.kts")
    if os.path.isfile(s1):
        return s1
    if os.path.isfile(s2):
        return s2
    return None


def _detect_root_build_file(root: str) -> Optional[str]:
    """Return build.gradle or build.gradle.kts if present at root."""
    b1 = os.path.join(root, "build.gradle")
    b2 = os.path.join(root, "build.gradle.kts")
    if os.path.isfile(b1):
        return b1
    if os.path.isfile(b2):
        return b2
    return None


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _parse_includes(settings_text: str) -> List[str]:
    """
    Extract project paths from include calls.

    Supports:
      include 'app', 'lib'
      include(':app', ':lib')
      include ":service", ":shared:core"

    Returns Gradle project paths like:
      [':app', ':lib', ':shared:core']
    """
    modules: List[str] = []
    for m in _INCLUDE_CALL_PATTERN.finditer(settings_text):
        args = m.group("args") or ""
        # Collect tokens inside quotes
        for q in _QUOTED_TOKEN_PATTERN.finditer(args):
            token = q.group("token").strip()
            if token:
                # Normalize to Gradle project path format (ensure leading colon)
                if not token.startswith(":"):
                    token = f":{token}"
                modules.append(token)
    # Remove duplicates while preserving order
    seen = set()
    deduped = []
    for p in modules:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def _project_path_to_dir(root: str, project_path: str) -> str:
    """
    Map a Gradle project path to a directory under root.

    Default Gradle convention:
      ':app'            -> 'app'
      ':libs:core'      -> 'libs/core'

    NOTE: This ignores explicit projectDir overrides in settings.
    """
    # Strip leading ':' and split remaining segments
    parts = [p for p in project_path.split(":") if p]
    rel = os.path.join(*parts) if parts else ""
    return os.path.join(root, rel)


def _find_build_file(candidate_dir: str) -> Optional[str]:
    """Return the build file path if found under candidate_dir."""
    g = os.path.join(candidate_dir, "build.gradle")
    k = os.path.join(candidate_dir, "build.gradle.kts")
    if os.path.isfile(g):
        return g
    if os.path.isfile(k):
        return k
    return None


def _fallback_search_by_last_segment(root: str, last_segment: str, max_depth: int = 3) -> Optional[str]:
    """
    As a best-effort fallback (for custom projectDir), search for a directory whose
    name matches the last segment and contains a build.gradle(.kts), scanning up to max_depth.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        depth = os.path.relpath(dirpath, root).count(os.sep)
        if depth > max_depth:
            continue
        if os.path.basename(dirpath) != last_segment:
            continue
        bf = _find_build_file(dirpath)
        if bf:
            return bf
    return None


# --------------------------
# Public scanner
# --------------------------

def scan_gradle_repo(path: str) -> Dict:
    """
    Scan a Java repository to detect Gradle modules.

    Args:
        path: Filesystem path to the repository root.

    Returns:
        {
          "ecosystem": "gradle",
          "root": "<abs path to settings.gradle(.kts) or build.gradle(.kts)>",
          "modules": [
              {"name": "<project-path or dir name>", "path": "<abs build file path>"}
          ],
          "summary": "human-readable summary"
        }
        or
        {"error": "Reason"} on failure.
    """
    if not os.path.isdir(path):
        return {"error": f"Path not found: {path}"}
    path = os.path.abspath(path)

    settings = _detect_settings_file(path)
    root_build = _detect_root_build_file(path)

    # Case 1: Proper multi-project (settings.* present)
    if settings:
        text = _read_text(settings)
        includes = _parse_includes(text)  # e.g., [':app', ':libs:core']
        modules = []

        if includes:
            for proj_path in includes:
                # Default mapping: ':libs:core' -> root/libs/core/build.gradle(.kts)
                candidate_dir = _project_path_to_dir(path, proj_path)
                bf = _find_build_file(candidate_dir)

                if not bf:
                    # If default mapping fails, try shallow search by last segment name
                    last = proj_path.split(":")[-1]
                    bf = _fallback_search_by_last_segment(path, last_segment=last)

                if bf:
                    modules.append({"name": proj_path, "path": os.path.abspath(bf)})
                else:
                    # Still record the intended module for visibility
                    modules.append({"name": proj_path, "path": os.path.abspath(candidate_dir)})

            summary = f"Gradle multi-project with {len(modules)} modules (derived from settings)."
        else:
            # settings present but no include → treat as single-module if root build file exists
            if root_build:
                modules = [{"name": os.path.basename(path), "path": os.path.abspath(root_build)}]
                summary = "Gradle single-project (settings present, no includes)."
            else:
                modules = []
                summary = "Gradle settings found but no modules or root build file detected."

        return {
            "ecosystem": "gradle",
            "root": os.path.abspath(settings),
            "modules": modules,
            "summary": summary,
        }

    # Case 2: No settings.*; maybe single-module project with only build.gradle(.kts)
    if root_build:
        modules = [{"name": os.path.basename(path), "path": os.path.abspath(root_build)}]
        return {
            "ecosystem": "gradle",
            "root": os.path.abspath(root_build),
            "modules": modules,
            "summary": "Gradle single-project (no settings file).",
        }

    # Not a Gradle repo
    return {"error": "No Gradle settings/build files found; not a Gradle project."}


if __name__ == "__main__":
    # Lightweight manual test:
    repo = os.getcwd()  # or set to a known Gradle project path
    result = scan_gradle_repo(repo)
    print(result)
