"""
Utils package for common filesystem and command execution utilities.
"""

from mcp_server.utils.exec import run_command, run_git_clone, is_git_repo, clone_to_temp
from mcp_server.utils.filesystem import (
    find_files,
    read_xml_safe,
    xml_text,
    detect_ecosystem,
    is_url,
    clone_or_use_local,
    get_project_name,
)

__all__ = [
    "run_command",
    "run_git_clone",
    "is_git_repo",
    "clone_to_temp",
    "find_files",
    "read_xml_safe",
    "xml_text",
    "detect_ecosystem",
    "is_url",
    "clone_or_use_local",
    "get_project_name",
]
