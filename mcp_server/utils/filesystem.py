"""
filesystem.py
Utilities for filesystem operations and repository detection.
"""

from __future__ import annotations
import os
import glob
import xml.etree.ElementTree as ET
from typing import List, Optional
from mcp_server.utils.exec import is_git_repo, clone_to_temp


def find_files(root: str, pattern: str, recursive: bool = True) -> List[str]:
    """
    Find all files matching a pattern in a directory tree.
    
    Args:
        root: Root directory to search from
        pattern: File pattern to match (e.g., "pom.xml", "*.json", "package.json")
        recursive: Whether to search recursively (default True)
    
    Returns:
        List of absolute paths to matching files
    """
    if not os.path.isdir(root):
        return []
    
    matches = []
    
    if recursive:
        # Use ** for recursive glob
        search_pattern = os.path.join(root, "**", pattern)
        matches = glob.glob(search_pattern, recursive=True)
    else:
        # Search only in the root directory
        search_pattern = os.path.join(root, pattern)
        matches = glob.glob(search_pattern)
    
    return [os.path.abspath(f) for f in matches if os.path.isfile(f)]


def read_xml_safe(path: str) -> Optional[ET.Element]:
    """
    Safely parse an XML file and return the root element.
    
    Args:
        path: Path to XML file
    
    Returns:
        XML root element, or None if parsing fails
    """
    try:
        return ET.parse(path).getroot()
    except Exception:
        return None


def xml_text(parent: ET.Element, tag: str) -> str:
    """
    Extract text content from a child XML element.
    
    Args:
        parent: Parent XML element
        tag: Tag name to find
    
    Returns:
        Text content of the element, or empty string if not found
    """
    el = parent.find(tag)
    return (el.text or "").strip() if el is not None and el.text else ""


def detect_ecosystem(path: str) -> Optional[str]:
    """
    Auto-detect the ecosystem/build system of a repository.
    
    Args:
        path: Path to repository root
    
    Returns:
        One of: "maven", "gradle", "node", "python", or None if unknown
    """
    if not os.path.isdir(path):
        return None
    
    # Check for Maven
    if os.path.isfile(os.path.join(path, "pom.xml")):
        return "maven"
    
    # Check for Gradle
    gradle_files = ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"]
    if any(os.path.isfile(os.path.join(path, f)) for f in gradle_files):
        return "gradle"
    
    # Check for Node.js
    if os.path.isfile(os.path.join(path, "package.json")):
        return "node"
    
    # Check for Python
    python_files = ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"]
    if any(os.path.isfile(os.path.join(path, f)) for f in python_files):
        return "python"
    
    return None


def is_url(path_or_url: str) -> bool:
    """
    Check if a string is a URL (http/https/git).
    
    Args:
        path_or_url: String to check
    
    Returns:
        True if it looks like a URL, False otherwise
    """
    return path_or_url.startswith(("http://", "https://", "git://", "git@"))


def clone_or_use_local(repo_path_or_url: str) -> dict:
    """
    Handle both local paths and remote Git URLs.
    
    If it's a URL, clone it to a temp directory.
    If it's a local path, use it directly.
    
    Args:
        repo_path_or_url: Either a local filesystem path or a Git URL
    
    Returns:
        {
            "success": bool,
            "path": str (absolute path to use),
            "is_temp": bool (whether path is temporary and should be cleaned up),
            "error": str (if any)
        }
    """
    # Check if it's a URL
    if is_url(repo_path_or_url):
        # Clone to temp
        result = clone_to_temp(repo_path_or_url)
        if result["success"]:
            return {
                "success": True,
                "path": result["path"],
                "is_temp": True
            }
        else:
            return {
                "success": False,
                "path": "",
                "is_temp": False,
                "error": result.get("error", "Failed to clone repository")
            }
    else:
        # Use local path
        abs_path = os.path.abspath(repo_path_or_url)
        if os.path.isdir(abs_path):
            return {
                "success": True,
                "path": abs_path,
                "is_temp": False
            }
        else:
            return {
                "success": False,
                "path": "",
                "is_temp": False,
                "error": f"Local path not found: {abs_path}"
            }


def get_project_name(path: str) -> str:
    """
    Extract a reasonable project name from a repository path.
    
    Args:
        path: Path to repository
    
    Returns:
        Project name (directory name or derived from path)
    """
    return os.path.basename(os.path.abspath(path))
