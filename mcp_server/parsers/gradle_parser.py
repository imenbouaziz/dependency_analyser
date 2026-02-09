
"""
gradle_parser.py
Basic Gradle parser: extracts direct dependencies from build.gradle(.kts) using simple regex.

⚠️ Scope & Limitations (by design, for simplicity):
- Parses ONLY direct dependencies declared in standard configurations:
  implementation, api, compileOnly, runtimeOnly, testImplementation, testRuntimeOnly, etc.
- Supports the common "group:artifact:version" notation inside quotes.
- Ignores version catalogs (libs.versions.toml), platforms/BOMs, variables, ext, Kotlin DSL maps, etc.
- Does not compute transitive dependencies.

Later improvements you can add:
- Parse version catalogs: settings/libs.versions.toml + type-safe accessors.
- Resolve variables (e.g., versions from gradle.properties).
- Run `gradle dependencies --console=plain` and parse.
"""

from __future__ import annotations
import os
import re
from typing import Dict, List

# Match lines like:
# implementation "group:artifact:1.2.3"
# testImplementation 'group:artifact:4.5.6'
# api("group:artifact:7.8.9")
_DEP_COORD_PATTERN = re.compile(
    r"""
    ^\s*                                          # optional leading space
    (?P<config>api|implementation|compileOnly|runtimeOnly|
                 testImplementation|testCompileOnly|testRuntimeOnly|
                 annotationProcessor|kapt|compile|runtime)   # configuration
    \s*\(?\s*                                     # optional '('
    ["']                                          # opening quote
    (?P<coord>[^"']+?)                            # group:artifact:version (best effort)
    ["']                                          # closing quote
    .*?$                                          # rest of the line
    """,
    re.MULTILINE | re.VERBOSE,
)


def _split_coord(coord: str):
    """
    Split 'group:artifact:version' into parts.
    Accepts missing version (e.g. 'group:artifact'), returns '' for version if absent.
    """
    parts = coord.strip().split(":")
    group = parts[0] if len(parts) > 0 else ""
    artifact = parts[1] if len(parts) > 1 else ""
    version = parts[2] if len(parts) > 2 else ""
    return group, artifact, version


def parse_gradle_module(build_file: str) -> Dict:
    """
    Parse a Gradle build file and extract direct dependencies declared in common configurations.

    Args:
        build_file: Absolute path to build.gradle or build.gradle.kts

    Returns:
        {
          "ecosystem": "gradle",
          "module": "<folder-name>",
          "dependencies": [
            {
              "group": "g",
              "artifact": "a",
              "version": "v",     # may be empty if version from catalog/variable
              "configuration": "implementation|api|... (as captured)"
            },
            ...
          ],
          "summary": "human-readable"
        }
        or
        {"error": "..."} on failure.
    """
    if not os.path.isfile(build_file):
        return {"error": f"Gradle build file not found: {build_file}"}

    try:
        text = open(build_file, "r", encoding="utf-8").read()
    except Exception as e:
        return {"error": f"Failed to read {build_file}: {e}"}

    module_name = os.path.basename(os.path.dirname(build_file)) or os.path.basename(build_file)
    deps: List[Dict] = []

    for m in _DEP_COORD_PATTERN.finditer(text):
        config = m.group("config")
        coord = m.group("coord")
        group, artifact, version = _split_coord(coord)
        if group and artifact:  # keep only plausible coords
            deps.append({
                "group": group,
                "artifact": artifact,
                "version": version,  # may be empty if defined elsewhere
                "configuration": config,
            })

    summary = f"Gradle module '{module_name}' with {len(deps)} direct dependencies."

    return {
        "ecosystem": "gradle",
        "module": module_name,
        "dependencies": deps,
        "summary": summary,
        "source": os.path.abspath(build_file),
    }


if __name__ == "__main__":
    # Quick manual test (run in a folder containing build.gradle or build.gradle.kts)
    here = os.getcwd()
    for fname in ("build.gradle", "build.gradle.kts"):
        path = os.path.join(here, fname)
        if os.path.isfile(path):
            print(parse_gradle_module(path))
